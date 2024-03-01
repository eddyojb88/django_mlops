from functools import wraps
import logging
from django.db import transaction, IntegrityError
import json
from django.utils import timezone
from .models import FlowTask, Flow, ExecutedFlow, ExecutedTask
from .task_utils import get_cytoscape_nodes_and_edges, function_accepts_kwargs, filter_kwargs_for_function
from django.conf import settings
from django.utils import timezone

from django.db import transaction
from .models import Flow, FlowTask

flow_pipeline_lookup = {}

def register_task(flow, task_name, task_info, nested):
    """
    Registers or updates a single task within a specified flow, handling dependencies.

    This function is responsible for creating a new task or updating an existing one within the given flow. It also sets up dependencies between the task and others as specified in the `task_info` parameter.

    Parameters:
    - flow (Flow): The flow object to which the task belongs.
    - task_name (str): The name of the task to be registered or updated.
    - task_info (dict): A dictionary containing information about the task, including dependencies.
    - nested (bool): A flag indicating whether the task is nested within another task.

    Returns:
    - FlowTask: The created or updated task object.
    """
    # Extract dependency information from task_info
    depends_on = task_info.get('depends_on', [])
    depends_bidirectionally_with = task_info.get('depends_bidirectionally_with', [])
    
    # Create or update the task in the database
    task, _ = FlowTask.objects.get_or_create(
        task_name=task_name, 
        flow=flow,  # Associate with the specified flow
        nested=nested,
    )

    # Set dependencies if any are specified
    if depends_on or depends_bidirectionally_with:
        set_dependencies(task, depends_on, depends_bidirectionally_with, flow)

    return task

def register_task_pipeline(flow_name, pipeline, clear_existing_flow_in_db=False):
    """
    Registers a pipeline of tasks for a specific flow, handling nested tasks and dependencies.

    This function sets up a complete pipeline of tasks for a given flow. It can also clear existing tasks and their relationships before setting up the new pipeline if required. The pipeline setup includes creating or updating tasks, setting dependencies, and ensuring that tasks no longer part of the pipeline are removed.

    Parameters:
    - flow_name (str): The name of the flow for which the pipeline is being registered.
    - pipeline (list of dict): A list of dictionaries, each representing a task and its details including dependencies and any nested tasks.
    - clear_existing_flow_in_db (bool, optional): Flag to clear existing tasks and relationships from the database for the given flow before registering the new pipeline. Defaults to False.

    Returns:
    - set: A set containing the names of the tasks that were updated or created as part of the pipeline.
    """
    # Create or retrieve the specified flow, and optionally clear existing tasks
    flow, created = Flow.objects.get_or_create(flow_name=flow_name)

    # Store the pipeline for reference
    global flow_pipeline_lookup
    flow_pipeline_lookup[flow_name] = pipeline
    
    if clear_existing_flow_in_db and not created:
        # If requested, delete all existing tasks for this flow to start fresh
        flow_tasks = FlowTask.objects.filter(flow=flow)
        flow_tasks.delete()
    
    with transaction.atomic():
        # Retrieve existing tasks for the flow to identify which ones to update or delete
        existing_tasks = set(FlowTask.objects.filter(flow=flow).values_list('task_name', flat=True))
        updated_tasks = set()

        def register_tasks_recursively(tasks, parent_flow, nested=False):
            """
            Recursively registers or updates tasks, including handling nested tasks.

            This internal function flowes each task in the provided task structure, registering them with the parent flow. It handles the creation or update of tasks, setting up their dependencies, and recursively flowes any nested tasks.

            Parameters:
            - tasks (dict): A dictionary of tasks to flow, where each key is a task name and each value is a task detail dictionary.
            - parent_flow (Flow): The flow object to which these tasks belong.
            - nested (bool): Indicates if the current tasks are nested within another task.
            """
            for task_name in tasks:
                # Register each task and add it to the set of updated tasks
                task = register_task(parent_flow, task_name, tasks[task_name], nested=nested)
                updated_tasks.add(task.task_name)

                # Flow any nested tasks
                nested_tasks = tasks[task_name].get('nested_tasks', [])
                if nested_tasks:
                    # Ensure nested tasks depend on their parent task if not already set
                    for j in nested_tasks:
                        nested_task = nested_tasks[j]
                        if task.task_name in nested_task['depends_bidirectionally_with']:
                            pass  # Dependency already exists
                        elif task.task_name not in nested_task['depends_on']:
                            nested_task['depends_on'].append(task.task_name)
                    register_tasks_recursively(nested_tasks, parent_flow, nested=True)

        # Start the pipeline flowing with the initial set of tasks
        register_tasks_recursively(pipeline, flow)

        # Identify and remove tasks that are no longer part of the pipeline
        tasks_to_delete = existing_tasks - updated_tasks
        if tasks_to_delete:
            FlowTask.objects.filter(flow=flow, task_name__in=tasks_to_delete).delete()

        return updated_tasks

def set_dependencies(task, depends_on, depends_bidirectionally_with, flow):
    """
    Sets dependencies for a given task within a flow. Dependencies can be unidirectional or bidirectional.
    
    This function links a task with its dependencies by creating or retrieving the dependent tasks and associating them
    accordingly. It ensures that each task is properly linked to others upon which it depends or with which it has
    bidirectional dependencies within the same flow.
    
    Parameters:
    - task (FlowTask): The task object for which dependencies are being set.
    - depends_on (list of str): A list of task names that the given task depends on. These are unidirectional dependencies.
    - depends_bidirectionally_with (list of str): A list of task names that have a bidirectional dependency with the given task.
    - flow (Flow): The flow instance to which these tasks belong.
    
    Returns:
    None
    """
    # print('here')
    for dep_name in depends_on:
        dep_task, _ = FlowTask.objects.get_or_create(
            task_name=dep_name, 
            flow=flow  # Link to the Flow instance
        )
        task.depends_on.add(dep_task)

    for dep_name in depends_bidirectionally_with:
        dep_task, _ = FlowTask.objects.get_or_create(
            task_name=dep_name, 
            flow=flow  # Link to the Flow instance
        )
        task.depends_bidirectionally_with.add(dep_task)
    
    return

def fetch_flow_pipeline(flow_name):
    """
    Retrieves the flow pipeline for a given flow name.
    
    Parameters:
    - flow_name (str): The name of the flow for which the pipeline configuration is to be retrieved.
    
    Returns:
    - The pipeline configuration if found, otherwise None.
    """
    return flow_pipeline_lookup.get(flow_name)

def resolve_dependencies_get_task_order(flow_name):
    """
    Resolves task dependencies and determines the execution order for tasks within a given flow.
    
    This function identifies and resolves the dependencies among tasks in a flow to determine a valid execution order.
    It handles circular dependency detection and raises an exception if such a scenario is detected. The resolution
    flow ensures that all dependencies are accounted for before a task is marked as ready for execution.
    
    Parameters:
    - flow_name (str): The name of the flow for which tasks and their execution order are to be resolved.
    
    Returns:
    - all_task_objs (QuerySet): A QuerySet of all task objects associated with the given flow.
    - task_order (list of str): A list of task names in the order they should be executed, based on their dependencies.
    
    Raises:
    - Exception: If a circular dependency is detected among the tasks.
    """

    flow = Flow.objects.get(flow_name=flow_name)
    all_task_objs = FlowTask.objects.filter(flow=flow)
    dependency_map = {task.id: set(task.depends_on.values_list('id', flat=True)) for task in all_task_objs}
    resolved_tasks = []
    unresolved_tasks = []

    def resolve(task_id):
        if task_id in resolved_tasks:
            return
        if task_id in unresolved_tasks:
            raise Exception("Circular dependency detected")
        unresolved_tasks.append(task_id)

        for dependency in dependency_map.get(task_id, []):
            resolve(dependency)

        resolved_tasks.append(task_id)
        unresolved_tasks.remove(task_id)

    for task in all_task_objs:
        resolve(task.id)

    # Map resolved task IDs back to task names or objects as needed for execution
    task_order = [FlowTask.objects.get(id=task_id).task_name for task_id in resolved_tasks]
    return all_task_objs, task_order

def make_flow_snapshot(tasks_lookup, task_order):

    '''
    Creates a snapshot of the flow tasks based on the provided task order and lookup details.
    Each ExecutedFlow needs to store a snapshot of the tasks
    Each ExecutedTask might have an output which we need to explore data from from a click of the node on the graph viz
    Therefore, store the task run ids with the nodes too, otherwise, if the original task changes later on then there is no valid ref

    Parameters:
    - tasks_lookup (dict): A dictionary where keys are task names and values are dictionaries containing task details.
    - task_order (list): A list of task names representing the order in which tasks should be executed.

    Returns:
    - dict: A dictionary representing the snapshot of the flow, including tasks and their execution order.
 
    '''

    # Initialize the flow snapshot with task details
    flow_snapshot = {
        'tasks': [],
        'order': task_order
    }

    for task_name in task_order:
        task_details = tasks_lookup.get(task_name)
        if task_details:
            # Assume task_details includes necessary information; adjust as needed
            task_snapshot = {
                'name': task_name,
                'depends_on': task_details.get('depends_on', []),
            }
            flow_snapshot['tasks'].append(task_snapshot)
    
    return flow_snapshot

def run_flow_pipeline(flow_name, **kwargs):
    '''
    Initiates and executes a flow pipeline by name, handling task execution and flow status updates.

    Parameters:
    - flow_name (str): The name of the flow to be executed.
    - **kwargs: Additional keyword arguments that may be required for task execution.

    Returns:
    - None
    '''

    try:
        # Attempt to fetch the flow definition and create a flow run instance
        flow = Flow.objects.get(flow_name=flow_name)
        flow_run = ExecutedFlow.objects.create(flow=flow, flow_id_snapshot=flow.id, flow_name_snapshot=flow.flow_name) 
        # Resolve task dependencies and determine the execution order
        all_task_objs, task_order = resolve_dependencies_get_task_order(flow_name)
        
    except Exception as e:
        logging.error(f"Failed to initiate flow run for {flow_name}: {e}")
        raise Exception('You may not have imported the pipeline in to the program, have spelt the flow wrong or are referring to a pipeline that no longer exists.')

    flow_pipeline = fetch_flow_pipeline(flow_name)
    flow_snapshot = make_flow_snapshot(flow_pipeline, task_order)
    flow_snapshot['graph'] = get_cytoscape_nodes_and_edges(all_task_objs, show_nested=True)
    flow_snapshot['flow_name'] = flow_name
    flow_run.flow_snapshot = flow_snapshot
    flow_run.save()
    kwargs['executed_flow_id'] = flow_run.id

    logging.info(f"Starting task execution for flow '{flow_name}'.")

    for task_name in task_order:
        # Execute each task according to the resolved order and pipeline definitions
        # If its in the flow_pipeline then its not a nested task:
        if task_name in flow_pipeline:
            task_dict = flow_pipeline[task_name]

        executed = execute_task(task_dict, task_name, flow, flow_run, **kwargs)
        flow_run.last_checkpoint_datetime = timezone.now()
        flow_run.save()

        if not executed:
            flow_run.status = 'failed'
            flow_run = post_flow_graph_to_add_status(flow_run)
            flow_run.save()
            return

    # Update the flow run status to 'complete' after successful execution of all tasks
    flow_run.end_time = timezone.now()
    flow_run.flow_complete = True
    flow_run.status = 'complete'
    flow_run = post_flow_graph_to_add_status(flow_run)
    flow_run.save()

    logging.info(f"All tasks for flow {flow_name} completed successfully.")

    return

def post_flow_graph_to_add_status(flow_run):
    '''
    An inefficient add on in order to color nodes based on task status
    Updates the flow run snapshot with the execution status of each task for visualization purposes.

    Parameters:
    - flow_run (ExecutedFlow): The flow run instance to update.

    Returns:
    - ExecutedFlow: The updated flow run instance with task status information.
    '''

    # create index map:
    index_map = {}
    snapshot = flow_run.flow_snapshot
    nodes = snapshot['graph']['nodes']
    etasks = ExecutedTask.objects.filter(flow_run=flow_run,)
    for count, i in enumerate(nodes):
        index_map[i['data']['id']] = count
        etask = etasks.filter(task_snapshot_id=i['data']['id'])
        if len(etask) > 0:
            i['data']['status'] = etask[0].status
    snapshot['graph']['nodes'] = nodes
    flow_run.flow_snapshot = snapshot
    flow_run.save()

    return flow_run

def make_task_snapshot(flow_task_obj,):

    """
    Creates a snapshot of the given task's details.

    Args:
        flow_task_obj: An instance of FlowTask representing the task for which a snapshot is being created.

    Returns:
        A dictionary containing the snapshot of the task, including its ID, name, dependencies, bidirectional dependencies, and nested status.
    """

    task_snapshot = {
        'task_id': flow_task_obj.id,
        'task_name': flow_task_obj.task_name,
        # Assuming 'task' has the necessary information; adjust as necessary
        'depends_on': [dependency.task_name for dependency in flow_task_obj.depends_on.all()],
        'depends_bidirectionally_with': [dependency.task_name for dependency in flow_task_obj.depends_bidirectionally_with.all()],
        'nested': flow_task_obj.nested
    }

    return task_snapshot

def execute_task(task_dict, task_name, flow, flow_run, **kwargs):

    """
    Executes a specific task as part of a flow run, handling logging, execution, and status updates.

    Args:
        task_dict: A dictionary containing task-specific data, including the function to execute.
        task_name: The name of the task to be executed.
        flow: The flow instance to which the task belongs.
        flow_run: The current execution instance of the flow.
        **kwargs: Additional keyword arguments to be passed to the task function.

    Returns:
        True if the task was executed successfully, False otherwise.
    """

    flow_task_obj = FlowTask.objects.get(task_name=task_name, flow=flow)
    
    # Check if the task has already been executed
    if ExecutedTask.objects.filter(flow_run=flow_run, task=flow_task_obj).exists():
        logging.info(f"Task {task_name} already executed.")
        return  # Task already executed

    logging.info(f"Executing task: {task_name}...")

    task_snapshot = make_task_snapshot(flow_task_obj,)

    task_run = ExecutedTask.objects.create(
        flow_run=flow_run,
        task=flow_task_obj,
        task_snapshot_id=flow_task_obj.id,
        task_snapshot=task_snapshot,
        start_time=timezone.now(),
    )
    
    # Execute the task but check whether it accepts **kwargs or not
    # If not, then filter the kwargs according to the accepted input arguments and pass on through
    func = task_dict['function']
    
    accepts_kwargs = function_accepts_kwargs(func)
    
    if getattr(settings, 'MLOPS_DEBUG', False):

        task_output = run_task(accepts_kwargs, func, **kwargs)
        flow_run = post_flow_graph_to_add_status(flow_run) # inefficient but potentially useful for debugging

    else:

        try:
            task_output = run_task(accepts_kwargs, func, **kwargs)

        except Exception as e:
            logging.info(f"Failed Task: {task_name}.")
            task_run.status = 'failed'
            task_run.end_time = timezone.now()
            task_run.exceptions['main_run'] = str(e)
            task_run.save()
            return False

    task_run.output=task_output
    task_run.task_complete = True
    task_run.end_time = timezone.now()
    task_run.status = 'complete'
    task_run.save()

    logging.info(f"Task {task_name} executed successfully.")

    return True

def run_task(accepts_kwargs, func, **kwargs):
    """
    Executes the given task function, either with all provided keyword arguments or only those it accepts.

    Args:
        accepts_kwargs: A boolean indicating whether the function accepts arbitrary keyword arguments.
        func: The task function to be executed.
        **kwargs: Keyword arguments to be passed to the task function.

    Returns:
        The output of the task function.
    """

    if accepts_kwargs:
        task_output = func(**kwargs)
    
    else:
        filtered_kwargs = filter_kwargs_for_function(func, kwargs)
        task_output = func(**filtered_kwargs)

    return task_output

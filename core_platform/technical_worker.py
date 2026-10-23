"""Execute registered read-only analysis tasks; no shell or repair authority."""
from .tech_team_dispatch import DispatchDenied, READ_ONLY_CAPABILITIES


class TechnicalWorker:
    def __init__(self, dispatcher, worker_id, handlers, reviewer=None):
        if (not isinstance(handlers,dict) or not handlers
                or not set(handlers).issubset(READ_ONLY_CAPABILITIES)
                or not all(callable(handler) for handler in handlers.values())):
            raise DispatchDenied('Explicit read-only handler registry required')
        self.dispatcher,self.worker_id=dispatcher,worker_id
        self.handlers,self.reviewer=dict(handlers),reviewer

    def once(self):
        item=self.dispatcher.claim_next(self.worker_id,set(self.handlers))
        if item is None:return None
        task_id,claim,task=item['task_id'],item['claim'],item['task']
        task={'task_id':task_id,**task}
        try:
            result=self.handlers[task['capability']](task)
            if self.reviewer is None:
                verdict={'passed':False,'code':'REVIEW_NOT_CONNECTED'}
            else:
                # Independent local evidence review is not a signed authority grant.
                try:verdict=self.reviewer(task,result)
                except Exception:verdict={'passed':False,'code':'REVIEW_FAILED'}
            state=self.dispatcher.finish(task_id,claim,result,verdict)
        except DispatchDenied:
            # A reassigned/expired claim must not overwrite the new owner's work.
            raise
        except Exception:
            self.dispatcher.fail(task_id,claim)
            return {'task_id':task_id,'status':'FAILED','error_code':'HANDLER_FAILED'}
        return {'task_id':task_id,'status':state}

import uuid

from latency.schemas.log_failure_event import LogFailureEventModel, TraceFailureEventModel
from latency.database.engine import AsyncSQLiteSingleton
from latency.schemas.request import (
    ListLogFailureEventResultRequest,
    ListTraceFailureEventResultRequest,
    GetErrCodeMetricsRequest,
    ListTimeAggregatedFailureEventRequest,
    ListPodAggregatedFailureEventRequest,
)


class LogFailureEventManager:
    _LOG_FAILURE_EVENT_INSERT_SQL = """
        INSERT OR REPLACE INTO log_failure_event_table 
        (id, log_id, log_file, raw_text, host_name, timestamp, level, filename, pod_name, pid, tid, trace_id, cluster_name, message, status_code, failure_mode)
        VALUES (:id, :log_id, :log_file, :raw_text, :host_name, :timestamp, :level, :filename, :pod_name, :pid, :tid, :trace_id, :cluster_name, :message, :status_code, :failure_mode)
    """
    _LOG_FAILURE_EVENT_RAW_INSERT_SQL = """
        INSERT INTO log_failure_event_table 
        (id, log_id, log_file, raw_text, host_name, timestamp, level, filename, pod_name, pid, tid, trace_id, cluster_name, message, status_code, failure_mode)
        VALUES (:id, :log_id, :log_file, :raw_text, :host_name, :timestamp, :level, :filename, :pod_name, :pid, :tid, :trace_id, :cluster_name, :message, :status_code, :failure_mode)
    """
    _TRACE_FAILURE_EVENT_RAW_INSERT_SQL = """
        INSERT INTO trace_failure_event_table 
        (id, log_id, trace_id, pod_names, host_names, cluster_names, timestamp, status_code, failure_mode)
        VALUES (:id, :log_id, :trace_id, :pod_names, :host_names, :cluster_names, :timestamp, :status_code, :failure_mode)
    """

    @staticmethod
    async def add_log_failure_event(results: list[LogFailureEventModel]) -> list[str]:
        ids_added = []
        if not results:
            return ids_added
        
        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            try:
                params = []
                for log_failure_event in batch:
                    param = log_failure_event.model_dump(exclude_none=False, by_alias=True)
                    param["failure_mode"] = ",".join(param.get("failure_mode", []))
                    params.append(param)
                await AsyncSQLiteSingleton().execute_modify(
                    LogFailureEventManager._LOG_FAILURE_EVENT_INSERT_SQL,
                    params,
                )
                ids_added.extend([log_failure_event.id for log_failure_event in batch])
            except Exception as e:
                print(f"批量添加故障模式知识失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def add_log_failure_event_raw(results: list[dict]) -> list[str]:
        ids_added = []
        if not results:
            return ids_added

        try:
            params = []
            for event in results:
                param = event.copy()
                param.setdefault("id", str(uuid.uuid4()))
                failure_mode = param.get("failure_mode", [])
                if isinstance(failure_mode, list):
                    param["failure_mode"] = ",".join(failure_mode)
                elif failure_mode is None:
                    param["failure_mode"] = ""
                param.setdefault("host_name", "Unknown")
                params.append(param)
            await AsyncSQLiteSingleton().execute_modify(
                LogFailureEventManager._LOG_FAILURE_EVENT_RAW_INSERT_SQL,
                params,
            )
            ids_added.extend([param["id"] for param in params])
        except Exception as e:
            print(f"批量添加故障日志事件失败，错误信息: {str(e)}")
        return ids_added
    
    @staticmethod
    async def add_log_failure_event_if_not_exist(results: list[LogFailureEventModel]) -> list[str]:
        ids_added = []
        if not results:
            return ids_added
        
        batch_size = 1024
        sql_str = """
            INSERT OR IGNORE INTO log_failure_event_table 
            (id, log_id, log_file, raw_text, host_name, timestamp, level, filename, pod_name, pid, tid, trace_id, cluster_name, message, status_code, failure_mode)
            VALUES (:id, :log_id, :log_file, :raw_text, :host_name, :timestamp, :level, :filename, :pod_name, :pid, :tid, :trace_id, :cluster_name, :message, :status_code, :failure_mode)
        """
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            try:
                params = []
                for log_failure_event in batch:
                    param = log_failure_event.model_dump(exclude_none=False, by_alias=True)
                    param["failure_mode"] = ",".join(param.get("failure_mode", []))
                    params.append(param)
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([log_failure_event.id for log_failure_event in batch])
            except Exception as e:
                print(f"批量添加故障模式知识失败，错误信息: {str(e)}")
        return ids_added
    
    @staticmethod
    async def update_failure_mode_by_raw_log(log_id: str, raw_text: str, failure_mode: str) -> bool:
        """根据原始日志更新故障模式"""
        sql_str = """
            UPDATE log_failure_event_table 
            SET failure_mode = :failure_mode
            WHERE log_id = :log_id AND raw_text = :raw_text
        """
        params = {"log_id": log_id, "raw_text": raw_text, "failure_mode": failure_mode}
        result = await AsyncSQLiteSingleton().execute_modify(sql_str, params)
        return result

    @staticmethod
    async def delete_unclassified_log_events_by_log_id(log_id: str) -> bool:
        """删除指定日志文件下未归类的上下文日志"""
        sql_str = """
            DELETE FROM log_failure_event_table
            WHERE log_id = :log_id
              AND (failure_mode IS NULL OR failure_mode = '')
        """
        return await AsyncSQLiteSingleton().execute_modify(sql_str, {"log_id": log_id})
    
    @staticmethod
    async def add_trace_failure_event(results: list[TraceFailureEventModel]) -> list[str]:
        # 添加向数据库中加入trace_failure_event的逻辑，pod_names,host_names,cluster_names转化为TEXT时，多个元素用","分割，返回添加的trace_id列表
        ids_added = []
        if not results:
            return ids_added
        
        batch_size = 1024
        for i in range(0, len(results), batch_size):
            batch = results[i : i + batch_size]
            try:
                sql_str = """
                    INSERT OR REPLACE INTO trace_failure_event_table 
                    (id, log_id, trace_id, pod_names, host_names, cluster_names, timestamp, status_code, failure_mode)
                    VALUES (:id, :log_id, :trace_id, :pod_names, :host_names, :cluster_names, :timestamp, :status_code, :failure_mode)
                """
                params = []
                for trace_failure_event in batch:
                    param = {
                        "id": trace_failure_event.id,
                        "log_id": trace_failure_event.log_id,
                        "trace_id": trace_failure_event.trace_id,
                        "pod_names": ",".join(trace_failure_event.pod_names),
                        "host_names": ",".join(trace_failure_event.host_names),
                        "cluster_names": ",".join(trace_failure_event.cluster_names),
                        "timestamp": trace_failure_event.timestamp,
                        "status_code": trace_failure_event.status_code,
                        "failure_mode": trace_failure_event.failure_mode
                    }
                    params.append(param)
                
                await AsyncSQLiteSingleton().execute_modify(sql_str, params)
                ids_added.extend([trace_failure_event.trace_id for trace_failure_event in batch])
            except Exception as e:
                print(f"批量添加trace故障事件失败，错误信息: {str(e)}")
        return ids_added

    @staticmethod
    async def add_trace_failure_event_raw(results: list[dict]) -> list[str]:
        ids_added = []
        if not results:
            return ids_added

        try:
            params = []
            for event in results:
                param = event.copy()
                param.setdefault("id", str(uuid.uuid4()))
                for key in ("pod_names", "host_names", "cluster_names"):
                    value = param.get(key, [])
                    if isinstance(value, list):
                        param[key] = ",".join(value)
                    elif value is None:
                        param[key] = ""
                param.setdefault("status_code", "")
                param.setdefault("failure_mode", "")
                params.append(param)

            await AsyncSQLiteSingleton().execute_modify(
                LogFailureEventManager._TRACE_FAILURE_EVENT_RAW_INSERT_SQL,
                params,
            )
            ids_added.extend([param["trace_id"] for param in params])
        except Exception as e:
            print(f"批量添加trace故障事件失败，错误信息: {str(e)}")
        return ids_added
    
    @staticmethod
    async def list_trace_failure_events(
        req=ListTraceFailureEventResultRequest
    ) -> tuple[int, list[TraceFailureEventModel]]:
        # 添加从数据库中查询trace故障事件的逻辑，TraceFailureEventModel的pod_names,host_names,cluster_names字段中多个元素用","分割
        # 若kb_id非None，从log_file_table中查询req的kb_id对应的文件id，即log_id列表，log_id的值需要属于这个列表
        # 若req的pod_names，host_names，cluster_names非None，则数据中相应pod_names，host_names，cluster_names字段中的元素需要与req的相应字段有重合
        # 若req的status_codes非空，则数据中status_code应该是属于status_codes的元素
        # 若is_anonymous非空，则需要筛选failure_mode字段非空的数据
        # 若created_at_end/created_at_start非空，则数据的timestamp字段的时间需要小于created_at_end/大于created_at_start
        # 若created_sorted_desc为True，则返回的数据列表按timestamp降序，否则升序
        # page_cnt和page_num分别表示返回的数据页每行的数据量以及页码
        try:
            log_ids = []
            
            if req.kb_id is not None:
                log_id_sql = """
                    SELECT id FROM log_file_table 
                    WHERE kb_id = :kb_id AND existed_status = 1
                """
                log_id_results = await AsyncSQLiteSingleton().execute_query(
                    log_id_sql, {"kb_id": req.kb_id}
                )
                log_ids = [result["id"] for result in log_id_results]
            
            sql_str = """
                SELECT id, log_id, trace_id, pod_names, host_names, cluster_names, 
                    timestamp, status_code, failure_mode
                FROM trace_failure_event_table
                WHERE 1=1
            """
            params = {}
            
            if log_ids:
                placeholders = ', '.join([f':log_id_{i}' for i in range(len(log_ids))])
                sql_str += f" AND log_id IN ({placeholders})"
                for i, log_id in enumerate(log_ids):
                    params[f'log_id_{i}'] = log_id
            
            if req.trace_ids:
                placeholders = ', '.join([f':trace_id_{i}' for i in range(len(req.trace_ids))])
                sql_str += f" AND trace_id IN ({placeholders})"
                for i, trace_id in enumerate(req.trace_ids):
                    params[f'trace_id_{i}'] = trace_id
            
            if req.pod_names:
                pod_conditions = []
                for i, pod_name in enumerate(req.pod_names):
                    pod_conditions.append(f"(pod_names = :pod_name_exact_{i} OR pod_names LIKE :pod_name_start_{i} OR pod_names LIKE :pod_name_middle_{i} OR pod_names LIKE :pod_name_end_{i})")
                    params[f'pod_name_exact_{i}'] = pod_name
                    params[f'pod_name_start_{i}'] = f"{pod_name},%"
                    params[f'pod_name_middle_{i}'] = f"%,{pod_name},%"
                    params[f'pod_name_end_{i}'] = f"%,{pod_name}"
                sql_str += f" AND ({' OR '.join(pod_conditions)})"
            
            if req.host_names:
                host_conditions = []
                for i, host_name in enumerate(req.host_names):
                    host_conditions.append(f"(host_names = :host_name_exact_{i} OR host_names LIKE :host_name_start_{i} OR host_names LIKE :host_name_middle_{i} OR host_names LIKE :host_name_end_{i})")
                    params[f'host_name_exact_{i}'] = host_name
                    params[f'host_name_start_{i}'] = f"{host_name},%"
                    params[f'host_name_middle_{i}'] = f"%,{host_name},%"
                    params[f'host_name_end_{i}'] = f"%,{host_name}"
                sql_str += f" AND ({' OR '.join(host_conditions)})"
            
            if req.cluster_names:
                cluster_conditions = []
                for i, cluster_name in enumerate(req.cluster_names):
                    cluster_conditions.append(f"(cluster_names = :cluster_name_exact_{i} OR cluster_names LIKE :cluster_name_start_{i} OR cluster_names LIKE :cluster_name_middle_{i} OR cluster_names LIKE :cluster_name_end_{i})")
                    params[f'cluster_name_exact_{i}'] = cluster_name
                    params[f'cluster_name_start_{i}'] = f"{cluster_name},%"
                    params[f'cluster_name_middle_{i}'] = f"%,{cluster_name},%"
                    params[f'cluster_name_end_{i}'] = f"%,{cluster_name}"
                sql_str += f" AND ({' OR '.join(cluster_conditions)})"
            
            if req.status_codes:
                placeholders = ', '.join([f':status_code_{i}' for i in range(len(req.status_codes))])
                sql_str += f" AND status_code IN ({placeholders})"
                for i, status_code in enumerate(req.status_codes):
                    params[f'status_code_{i}'] = status_code
            
            if req.is_anomalous is not None:
                if req.is_anomalous:
                    sql_str += " AND failure_mode IS NOT NULL AND failure_mode != ''"
                else:
                    sql_str += " AND (failure_mode IS NULL OR failure_mode = '')"
            
            if req.created_at_start:
                sql_str += " AND timestamp >= :created_at_start"
                params['created_at_start'] = req.created_at_start
            
            if req.created_at_end:
                sql_str += " AND timestamp <= :created_at_end"
                params['created_at_end'] = req.created_at_end
            
            order_direction = "DESC" if req.created_sorted_desc else "ASC"
            sql_str += f" ORDER BY timestamp {order_direction}"
            
            count_sql = f"SELECT COUNT(*) as total FROM ({sql_str})"
            count_result = await AsyncSQLiteSingleton().execute_query(count_sql, params)
            total = count_result[0]["total"] if count_result else 0
            
            offset = (req.page_num - 1) * req.page_cnt
            sql_str += f" LIMIT :limit OFFSET :offset"
            params['limit'] = req.page_cnt
            params['offset'] = offset
            
            results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            
            trace_failure_events = []
            for result in results:
                pod_names_list = [name.strip() for name in result["pod_names"].split(',') if name.strip()] if result["pod_names"] else []
                host_names_list = [name.strip() for name in result["host_names"].split(',') if name.strip()] if result["host_names"] else []
                cluster_names_list = [name.strip() for name in result["cluster_names"].split(',') if name.strip()] if result["cluster_names"] else []
                
                trace_failure_event = TraceFailureEventModel(
                    id=result["id"],
                    log_id=result["log_id"],
                    trace_id=result["trace_id"],
                    pod_names=pod_names_list,
                    host_names=host_names_list,
                    cluster_names=cluster_names_list,
                    timestamp=result["timestamp"],
                    status_code=result["status_code"] if result["status_code"] else "",
                    failure_mode=result["failure_mode"] if result["failure_mode"] else ""
                )
                trace_failure_events.append(trace_failure_event)
            
            return total, trace_failure_events
        
        except Exception as e:
            print(f"查询trace故障事件失败，错误信息: {str(e)}")
            return 0, []

    @staticmethod
    async def list_log_failure_events(
        req=ListLogFailureEventResultRequest
    ) -> tuple[int, list[LogFailureEventModel]]:
        # 添加从数据库中查询log故障事件的逻辑
        # 输入的参数有kb_id和trace_id，其中kb_id可能是None
        # 首先若kb_id非None，从log_file_table中查询req的kb_id对应的文件id，即log_id列表
        # 然后，在log_failure_event_table中查询相应数据，构建list[LogFailureEventModel]。查询条件是，log_id属于log_id列表（若没有log_id列表，则所有log_id都符合条件），trace_id等于输入req的trace_id
        # 其中，failure_mode字段在LogFailureEventModel中是str列表，它是从sql语句查询的failure_mode字段结果，按","进行分割得到的字符串列表
        # 输出的log列表按照时间，从先到后排序，对应ist[LogFailureEventModel]
        # 输出的第一个int参数是列表的长度
        
        try:
            log_ids = []
            
            # 如果 kb_id 非 None，查询对应的 log_id 列表
            if req.kb_id is not None:
                log_id_sql = """
                    SELECT id FROM log_file_table 
                    WHERE kb_id = :kb_id AND existed_status = 1
                """
                log_id_results = await AsyncSQLiteSingleton().execute_query(
                    log_id_sql, {"kb_id": req.kb_id}
                )
                log_ids = [result["id"] for result in log_id_results]
            
            # 如果log_id非None，将log_id加入筛选条件
            if req.log_id is not None:
                log_ids.append(req.log_id)

            if req.kb_id is not None and not log_ids:
                return 0, []
            
            # 构建查询 log_failure_event_table 的 SQL
            sql_str = """
                SELECT id, log_id, log_file, raw_text, host_name, timestamp, level, 
                       filename, pod_name, pid, tid, trace_id, cluster_name, 
                       message, status_code, failure_mode
                FROM log_failure_event_table
                WHERE 1=1
            """
            params = {}
            
            # 添加 log_id 过滤条件
            if log_ids:
                placeholders = ', '.join([f':log_id_{i}' for i in range(len(log_ids))])
                sql_str += f" AND log_id IN ({placeholders})"
                for i, log_id in enumerate(log_ids):
                    params[f'log_id_{i}'] = log_id
            
            # 添加 trace_id 过滤条件
            if req.trace_ids:
                placeholders = ",".join([f':trace_id_{i}' for i in range(len(req.trace_ids))])
                sql_str += f" AND trace_id IN ({placeholders})"
                for i, trace_id in enumerate(req.trace_ids):
                    params[f'trace_id_{i}'] = trace_id
            
            # 按日志文件聚合，再按时间排序，便于前端按文件展示链路日志
            sql_str += " ORDER BY timestamp ASC, pid ASC, tid ASC"
            
            # 执行查询
            results = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            
            # 构建 LogFailureEventModel 列表
            log_failure_events = []
            for result in results:
                # 将 failure_mode 从字符串按 "," 分割成列表
                failure_mode_str = result.get("failure_mode", "")
                if failure_mode_str:
                    failure_mode_list = [fm.strip() for fm in failure_mode_str.split(',') if fm.strip()]
                else:
                    failure_mode_list = []
                
                # 创建 LogFailureEventModel 对象
                log_failure_event = LogFailureEventModel(
                    id=result["id"],
                    log_id=result["log_id"],
                    log_file=result["log_file"],
                    raw_text=result["raw_text"],
                    host_name=result["host_name"],
                    timestamp=result["timestamp"],
                    level=result["level"],
                    filename=result["filename"],
                    pod_name=result["pod_name"],
                    pid=result["pid"],
                    tid=result["tid"],
                    trace_id=result["trace_id"],
                    cluster_name=result["cluster_name"],
                    message=result["message"],
                    status_code=result["status_code"],
                    failure_mode=failure_mode_list
                )
                log_failure_events.append(log_failure_event)
            
            return len(log_failure_events), log_failure_events
        
        except Exception as e:
            print(f"查询日志故障事件失败，错误信息: {str(e)}")
            return 0, []

    @staticmethod
    async def get_err_code_metrics(
        req: GetErrCodeMetricsRequest,
    ) -> tuple[int, dict[str, list[dict]]]:
        # TODO:从trace_failure_event_table中读取满足要求的trace数据，并获取故障码的指标结果
        # 首先，按照req内容对trace_failure_event_table满足要求的故障trace数据进行筛选。
        # 1.仅保留failure_mode非空的数据
        # 2.若kb_id非空，从log_file_table中查询req的kb_id对应的文件id，即log_id列表，仅保留log_id在该列表中的数据
        # 3.若err_codes非空，仅保留status_code在该列表中的数据
        # 4.若host_names/cluster_names/pod_names列表非空，仅保留数据相应字段包含任意列表中元素的数据
        # 5.若start_time/end_time非空，仅保留timestamp > start_time/timestamp < end_time的数据
        # 然后，计算返回的指标数据。返回的第一个参数是每条曲线的数据点数量total，第二个参数是曲线具体数据的内容，内容是字典，字典的键是故障码，值是一个字典列表，表示一个故障码的曲线数据。
        # 该字典的键为time和err_cnt，分别表示数据点的时间以及前后各0.5秒共1秒内，故障码的trace数量。
        # 输出time字段的时间戳的格式为%Y-%M-%D %H:%M:%S，如2026-01-01 00:00:00，输入req的start_time/end_time字段若秒数后有微秒数，如.123456，起始和结束时间需要取整，分别是对start_time向下取整和对end_time向上取整，也就是输出的所有time都需要是整秒。
        # 输出数据的time时间点默认间隔为1秒，首先移除所有0值数据点，如果剩余数据点仍超过max_points，则对非0数据点进行智能采样以保留曲线关键信息。
        # 列表按time从小到大排序，err_cnt表示时间点前后各0.5秒共1秒内，匹配到故障码的故障trace数量总和。
        # 请尽量保证算法的效率。
        
        try:
            from datetime import datetime, timedelta
            import math
            import bisect
            from collections import defaultdict
            
            log_ids = []
            if req.kb_id:
                log_id_sql = """
                    SELECT id FROM log_file_table 
                    WHERE kb_id = :kb_id AND existed_status = 1
                """
                log_id_results = await AsyncSQLiteSingleton().execute_query(
                    log_id_sql, {"kb_id": req.kb_id}
                )
                log_ids = [result["id"] for result in log_id_results]
            
            sql_str = """
                SELECT trace_id, failure_mode, status_code, timestamp, 
                       pod_names, host_names, cluster_names
                FROM trace_failure_event_table
                WHERE failure_mode IS NOT NULL AND failure_mode != ''
            """
            params = {}
            
            if log_ids:
                placeholders = ', '.join([f':log_id_{i}' for i in range(len(log_ids))])
                sql_str += f" AND log_id IN ({placeholders})"
                for i, log_id in enumerate(log_ids):
                    params[f'log_id_{i}'] = log_id
            
            if req.err_codes:
                placeholders = ', '.join([f':err_code_{i}' for i in range(len(req.err_codes))])
                sql_str += f" AND status_code IN ({placeholders})"
                for i, err_code in enumerate(req.err_codes):
                    params[f'err_code_{i}'] = err_code
            
            if req.pod_names:
                pod_conditions = []
                for i, pod_name in enumerate(req.pod_names):
                    pod_conditions.append(f"(pod_names = :pod_name_exact_{i} OR pod_names LIKE :pod_name_start_{i} OR pod_names LIKE :pod_name_middle_{i} OR pod_names LIKE :pod_name_end_{i})")
                    params[f'pod_name_exact_{i}'] = pod_name
                    params[f'pod_name_start_{i}'] = f"{pod_name},%"
                    params[f'pod_name_middle_{i}'] = f"%,{pod_name},%"
                    params[f'pod_name_end_{i}'] = f"%,{pod_name}"
                sql_str += f" AND ({' OR '.join(pod_conditions)})"
            
            if req.host_names:
                host_conditions = []
                for i, host_name in enumerate(req.host_names):
                    host_conditions.append(f"(host_names = :host_name_exact_{i} OR host_names LIKE :host_name_start_{i} OR host_names LIKE :host_name_middle_{i} OR host_names LIKE :host_name_end_{i})")
                    params[f'host_name_exact_{i}'] = host_name
                    params[f'host_name_start_{i}'] = f"{host_name},%"
                    params[f'host_name_middle_{i}'] = f"%,{host_name},%"
                    params[f'host_name_end_{i}'] = f"%,{host_name}"
                sql_str += f" AND ({' OR '.join(host_conditions)})"
            
            if req.cluster_names:
                cluster_conditions = []
                for i, cluster_name in enumerate(req.cluster_names):
                    cluster_conditions.append(f"(cluster_names = :cluster_name_exact_{i} OR cluster_names LIKE :cluster_name_start_{i} OR cluster_names LIKE :cluster_name_middle_{i} OR cluster_names LIKE :cluster_name_end_{i})")
                    params[f'cluster_name_exact_{i}'] = cluster_name
                    params[f'cluster_name_start_{i}'] = f"{cluster_name},%"
                    params[f'cluster_name_middle_{i}'] = f"%,{cluster_name},%"
                    params[f'cluster_name_end_{i}'] = f"%,{cluster_name}"
                sql_str += f" AND ({' OR '.join(cluster_conditions)})"
            
            if req.start_time:
                sql_str += " AND timestamp >= :start_time"
                params['start_time'] = req.start_time
            
            if req.end_time:
                sql_str += " AND timestamp <= :end_time"
                params['end_time'] = req.end_time
            
            sql_str += " ORDER BY timestamp ASC"
            
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            
            if not rows:
                return 0, {}
            
            def parse_time(time_str):
                if not time_str:
                    return None
                try:
                    if '.' in time_str:
                        time_str = time_str.split('.')[0]
                    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except:
                    return None
            
            def round_down_to_second(dt):
                return dt.replace(microsecond=0)
            
            def round_up_to_second(dt):
                if dt.microsecond > 0:
                    return (dt + timedelta(seconds=1)).replace(microsecond=0)
                return dt
            
            timestamps = []
            for row in rows:
                ts = parse_time(row["timestamp"])
                if ts:
                    timestamps.append((ts, row["status_code"], row["failure_mode"]))
            
            if not timestamps:
                return 0, {}
            
            min_time = min(ts[0] for ts in timestamps)
            max_time = max(ts[0] for ts in timestamps)
            
            if req.start_time:
                start_dt = parse_time(req.start_time)
                if start_dt:
                    min_time = round_down_to_second(start_dt)
            
            if req.end_time:
                end_dt = parse_time(req.end_time)
                if end_dt:
                    max_time = round_up_to_second(end_dt)
            else:
                max_time = round_up_to_second(max_time)
            
            err_code_events = {}
            for ts, status_code, failure_mode in timestamps:
                if not status_code:
                    status_code = "UNKNOWN"
                if status_code not in err_code_events:
                    err_code_events[status_code] = []
                err_code_events[status_code].append(ts)
            
            for err_code in err_code_events:
                err_code_events[err_code].sort()
            
            def sample_curve(points: list[dict], max_points: int) -> list[dict]:
                if len(points) <= max_points:
                    return points
                
                non_zero_points = [p for p in points if p['err_cnt'] > 0]
                
                if len(non_zero_points) <= max_points:
                    return non_zero_points
                
                peak_indices = set()
                for i in range(1, len(non_zero_points) - 1):
                    prev_cnt = non_zero_points[i-1]['err_cnt']
                    curr_cnt = non_zero_points[i]['err_cnt']
                    next_cnt = non_zero_points[i+1]['err_cnt']
                    
                    if curr_cnt > prev_cnt and curr_cnt > next_cnt:
                        peak_indices.add(i)
                    elif curr_cnt < prev_cnt and curr_cnt < next_cnt:
                        peak_indices.add(i)
                
                if len(peak_indices) >= max_points:
                    sorted_peaks = sorted(peak_indices, key=lambda i: non_zero_points[i]['err_cnt'], reverse=True)
                    selected_indices = set(sorted_peaks[:max_points])
                    return sorted([non_zero_points[i] for i in selected_indices], key=lambda p: p['time'])
                
                remaining_slots = max_points - len(peak_indices)
                non_peak_indices = [i for i in range(len(non_zero_points)) if i not in peak_indices]
                
                if len(non_peak_indices) <= remaining_slots:
                    selected_indices = set(range(len(non_zero_points)))
                    return non_zero_points
                
                sorted_non_peak = sorted(non_peak_indices, key=lambda i: non_zero_points[i]['err_cnt'], reverse=True)
                selected_non_peak = set(sorted_non_peak[:remaining_slots])
                
                all_selected_indices = peak_indices | selected_non_peak
                result = [non_zero_points[i] for i in sorted(all_selected_indices)]
                
                return result
            
            result = {}
            total_points = 0
            
            for err_code, event_times_sorted in err_code_events.items():
                time_count_map = defaultdict(int)
                
                for event_time in event_times_sorted:
                    base_second = event_time.replace(microsecond=0)
                    
                    for offset in [-1, 0, 1]:
                        check_time = base_second + timedelta(seconds=offset)
                        
                        if min_time <= check_time <= max_time:
                            window_start = check_time - timedelta(seconds=0.5)
                            window_end = check_time + timedelta(seconds=0.5)
                            
                            if window_start <= event_time <= window_end:
                                time_count_map[check_time] += 1
                
                curve_data = [
                    {
                        "time": time_point.strftime("%Y-%m-%d %H:%M:%S"),
                        "err_cnt": count
                    }
                    for time_point, count in sorted(time_count_map.items())
                ]
                
                sampled_data = sample_curve(curve_data, req.max_points)
                result[err_code] = sampled_data
                
                if len(sampled_data) > total_points:
                    total_points = len(sampled_data)
            
            return total_points, result
        
        except Exception as e:
            print(f"获取故障码指标失败，错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, {}

    @staticmethod
    async def list_time_aggregated_failure_events(
        req: ListTimeAggregatedFailureEventRequest
    ) -> tuple[int, list[str], list[dict]]:
        # TODO: 添加从trace_failure_event_table数据库中查询每个时段故障码总数和详细情况的逻辑
        # 首先，对created_at_start到created_at_end按照interval的时间间隔进行遍历，每一段时间
        # 对应第三个返回值表示的统计结果中的一条数据，数据条数对应第一个返回值；若最后一段不够一个完整时间段，也向上补齐
        # 对于每一个时间段，统计ListTimeAggregatedFailureEventRequest数据库中，kb_id为req的kb_id，timestamp出现在时间段内的数据中，
        # 各个故障码的出现条数，其中trace的时间对应timestamp字段，故障码对应status_code。
        # 第三个返回值统计结果中，每个dict对应的键有start_time, end_time, 故障码字符串，以及"all"，值为每个时间段的开始时间、结束时间、故障码出现的次数，以及所有故障码出现次数的总和
        # 完成聚合后，遍历得到的统计结果，将除了"all"以外的所有故障码按转化为数字后的从小到大进行排序，第二个返回值表示排序后的故障码
        # 列表，列表第一个值是"all"，其余的是排序后的故障码字符串
        # req的sort_by, created_sorted_desc表示排序的依据和升降序。若sort_by为timestamp，则将统计结果按start_time字段排序，若created_sorted_desc为true，则降序排序，若为false，则升序排序
        # req的page_num和page_cnt表示返回结果是第几页和每页多少行
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        try:
            log_ids = []
            if req.kb_id:
                log_id_sql = """
                    SELECT id FROM log_file_table 
                    WHERE kb_id = :kb_id AND existed_status = 1
                """
                log_id_results = await AsyncSQLiteSingleton().execute_query(
                    log_id_sql, {"kb_id": req.kb_id}
                )
                log_ids = [result["id"] for result in log_id_results]
            
            if not log_ids and req.kb_id:
                return 0, ["all"], []
            
            if req.interval == "second":
                time_format_sql = "%Y-%m-%d %H:%M:%S"
            elif req.interval == "hour":
                time_format_sql = "%Y-%m-%d %H:00:00"
            else:
                time_format_sql = "%Y-%m-%d %H:%M:00"
            
            sql_str = f"""
                SELECT 
                    strftime('{time_format_sql}', timestamp) as time_bucket,
                    status_code,
                    COUNT(*) as cnt
                FROM trace_failure_event_table
                WHERE 1=1
            """
            params = {}
            
            if log_ids:
                placeholders = ', '.join([f':log_id_{i}' for i in range(len(log_ids))])
                sql_str += f" AND log_id IN ({placeholders})"
                for i, log_id in enumerate(log_ids):
                    params[f'log_id_{i}'] = log_id
            
            if req.created_at_start:
                sql_str += " AND timestamp >= :start_time"
                params['start_time'] = req.created_at_start
            
            if req.created_at_end:
                sql_str += " AND timestamp <= :end_time"
                params['end_time'] = req.created_at_end
            
            sql_str += " GROUP BY time_bucket, status_code"
            
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            
            if not rows:
                return 0, ["all"], []
            
            interval_delta = {
                "second": timedelta(seconds=1),
                "minute": timedelta(minutes=1),
                "hour": timedelta(hours=1),
            }.get(req.interval, timedelta(minutes=1))
            
            time_buckets: dict[str, dict[str, int]] = defaultdict(dict)
            all_status_codes = set()
            
            for row in rows:
                time_bucket = row["time_bucket"]
                status_code = row["status_code"] or ""
                cnt = row["cnt"]
                if status_code:
                    time_buckets[time_bucket][status_code] = cnt
                    all_status_codes.add(status_code)
            
            try:
                sorted_codes = sorted(list(all_status_codes), key=lambda x: int(x) if x.isdigit() else x)
            except:
                sorted_codes = sorted(list(all_status_codes))
            
            err_codes = ["all"] + sorted_codes
            
            time_format = "%Y-%m-%d %H:%M:%S"
            results = []
            for time_bucket, code_counts in time_buckets.items():
                bucket_start = datetime.strptime(time_bucket, time_format)
                bucket_end = bucket_start + interval_delta
                total_cnt = sum(code_counts.values())
                result = {
                    "start_time": time_bucket,
                    "end_time": bucket_end.strftime(time_format),
                    "status_code_cnt": {"all": total_cnt}
                }
                for code in sorted_codes:
                    cnt = code_counts.get(code, 0)
                    if cnt > 0:
                        result["status_code_cnt"][code] = cnt
                results.append(result)
            
            sort_fields = req.sort_fields if req.sort_fields and len(req.sort_fields) > 0 else []
            valid_sort_fields = []
            for sort_field in sort_fields:
                field_name = sort_field.field
                if field_name == "timestamp" or field_name in err_codes:
                    valid_sort_fields.append(sort_field)

            if valid_sort_fields:
                for sort_field in reversed(valid_sort_fields):
                    field_name = sort_field.field
                    is_desc = sort_field.order == "desc"
                    if field_name == "timestamp":
                        results.sort(key=lambda x: x["start_time"], reverse=is_desc)
                    else:
                        results.sort(
                            key=lambda x: x["status_code_cnt"].get(field_name, 0),
                            reverse=is_desc,
                        )
            else:
                sort_key = req.sort_by
                if sort_key == "timestamp":
                    results.sort(key=lambda x: x["start_time"], reverse=req.created_sorted_desc)
                elif sort_key == "all" or sort_key not in err_codes:
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get("all", 0),
                        reverse=req.created_sorted_desc,
                    )
                else:
                    def sort_func(x):
                        primary = x["status_code_cnt"].get(sort_key, 0)
                        secondary = x["status_code_cnt"].get("all", 0)
                        return primary, secondary

                    results.sort(key=sort_func, reverse=req.created_sorted_desc)
            total = len(results)
            start_idx = (req.page_num - 1) * req.page_cnt
            end_idx = start_idx + req.page_cnt
            results = results[start_idx:end_idx]
            
            return total, err_codes, results
            
        except Exception as e:
            print(f"查询时间段聚合故障事件失败，错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, ["all"], []
    
    @staticmethod
    async def list_pod_aggregated_failure_events(
        req: ListPodAggregatedFailureEventRequest
    ) -> tuple[int, list[dict]]:
        # TODO: 添加从trace_failure_event_table数据库中读取满足要求的数据，并按pod进行聚合统计故障码出现次数的逻辑
        # 首先，筛选timestamp在req的created_at_start到created_at_end之间，kb_id为req的kb_id的所有数据
        # 按照pod_names对结果进行聚合，形成一个列表，即第二个返回值的结果列表，第一个返回值表示列表的长度。
        # 列表中每一项是一个dict，存储一个pod的故障码信息。键有pod_name，对应查询结果的pod_names字段，以及status_code_cnt，对应故障码的统计
        # 其中，status_code_cnt是一个dict，键是all以及所有故障码字符串，值是所有故障码出现次数总和以及各个故障码出现次数。
        # 数据库中的pod_names字段可能有多个由","分割的pod_name，因为一个trace可能是跨pod的。对于这种情况，需要将这条trace的故障码计数
        # 拆分到各个pod的故障码计数中，也就是将各个pod_name对应的该故障码计数都加1。最终的结果中，pod_name应该都是单独的pod，没有多个pod的情况
        # 对查询结果进行排序，req的sort_by字段表示了结果列表的排序依据，为all或其他故障码，created_sorted_desc表示排序升序还是降序，True表示降序，False表示升序。
        # 如果排序依据的故障码在排序比较的两条结果中都没有出现，那么就按照all的数量进行排序
        # req的page_num和page_cnt表示返回结果是第几页和每页多少行
        # 请你在完成代码时注意计算的效率问题
        
        from collections import defaultdict
        
        try:
            log_ids = []
            if req.kb_id:
                log_id_sql = """
                    SELECT id FROM log_file_table 
                    WHERE kb_id = :kb_id AND existed_status = 1
                """
                log_id_results = await AsyncSQLiteSingleton().execute_query(
                    log_id_sql, {"kb_id": req.kb_id}
                )
                log_ids = [result["id"] for result in log_id_results]
            
            if not log_ids and req.kb_id:
                return 0, []
            
            sql_str = """
                SELECT pod_names, status_code, COUNT(*) as cnt
                FROM trace_failure_event_table
                WHERE 1=1
            """
            params = {}
            
            if log_ids:
                placeholders = ', '.join([f':log_id_{i}' for i in range(len(log_ids))])
                sql_str += f" AND log_id IN ({placeholders})"
                for i, log_id in enumerate(log_ids):
                    params[f'log_id_{i}'] = log_id
            
            if req.created_at_start:
                sql_str += " AND timestamp >= :start_time"
                params['start_time'] = req.created_at_start
            
            if req.created_at_end:
                sql_str += " AND timestamp <= :end_time"
                params['end_time'] = req.created_at_end
            
            sql_str += " AND pod_names IS NOT NULL AND pod_names != ''"
            sql_str += " AND status_code IS NOT NULL AND status_code != ''"
            
            sql_str += " GROUP BY pod_names, status_code"
            
            rows = await AsyncSQLiteSingleton().execute_query(sql_str, params)
            
            if not rows:
                return 0, []
            
            pod_status_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            all_status_codes = set()
            
            for row in rows:
                pod_names_str = row["pod_names"]
                status_code = row["status_code"]
                cnt = row["cnt"]
                
                pod_names_list = [name.strip() for name in pod_names_str.split(',') if name.strip()]
                
                for pod_name in pod_names_list:
                    pod_status_counts[pod_name][status_code] += cnt
                    pod_status_counts[pod_name]["all"] += cnt
                    all_status_codes.add(status_code)
            
            try:
                sorted_codes = sorted(list(all_status_codes), key=lambda x: int(x) if x.isdigit() else x)
            except:
                sorted_codes = sorted(list(all_status_codes))
            
            results = []
            for pod_name, code_counts in pod_status_counts.items():
                result = {
                    "pod_name": pod_name,
                    "status_code_cnt": {"all": code_counts.get("all", 0)}
                }
                for code in sorted_codes:
                    cnt = code_counts.get(code, 0)
                    if cnt > 0:
                        result["status_code_cnt"][code] = cnt
                results.append(result)
            
            sort_fields = req.sort_fields if req.sort_fields and len(req.sort_fields) > 0 else []
            valid_sort_fields = []
            valid_codes = ["all"] + sorted_codes
            for sort_field in sort_fields:
                if sort_field.field in valid_codes:
                    valid_sort_fields.append(sort_field)

            if valid_sort_fields:
                for sort_field in reversed(valid_sort_fields):
                    field_name = sort_field.field
                    is_desc = sort_field.order == "desc"
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get(field_name, 0),
                        reverse=is_desc,
                    )
            else:
                sort_key = req.sort_by
                if sort_key == "all" or sort_key not in valid_codes:
                    results.sort(
                        key=lambda x: x["status_code_cnt"].get("all", 0),
                        reverse=req.created_sorted_desc
                    )
                else:
                    def sort_func(x):
                        primary = x["status_code_cnt"].get(sort_key, 0)
                        secondary = x["status_code_cnt"].get("all", 0)
                        if primary == 0:
                            return (0, secondary)
                        else:
                            return (1, primary)

                    results.sort(key=sort_func, reverse=req.created_sorted_desc)

            total = len(results)
            start_idx = (req.page_num - 1) * req.page_cnt
            end_idx = start_idx + req.page_cnt
            results = results[start_idx:end_idx]
            
            return total, results
        
        except Exception as e:
            print(f"查询pod聚合故障事件失败，错误信息: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0, []

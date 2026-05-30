#include "kvcache_conn_fault_011.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_011 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135)
static AutoRegister<KvcacheConnFault011> g_kvcacheconnfault011("kvcache_conn_fault_011");

bool KvcacheConnFault011::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG | sort | uniq -c | grep -w 25");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=25的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"25\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault011::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    return "错误码25 K_MASTER_TIMEOUT (三方etcd)";
}

std::string KvcacheConnFault011::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    return "etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L135）";
}

RootCause KvcacheConnFault011::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault011::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络。（来源：08手册:L273）";
}

std::string KvcacheConnFault011::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L454, L456, L135
    return "通过access log识别（来源：08手册:L135, L196）：access log中status_code（第8列）为25；配合Worker日志中etcd is timeout/unavailable和resource.log中ETCD_QUEUE堆积。（来源：08手册:L135, L217, L149）";
}

std::string KvcacheConnFault011::GetId() const
{
    return "kvcache_conn_fault_011";
}

} // namespace diag

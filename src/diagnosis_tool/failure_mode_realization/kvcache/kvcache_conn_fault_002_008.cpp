#include "kvcache_conn_fault_002_008.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_008 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130)
static AutoRegister<KvcacheConnFault002_008> g_kvcacheconnfault002_008("kvcache_conn_fault_002_008");

bool KvcacheConnFault002_008::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG | sort | uniq -c | grep -w 8");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=8的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"8\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_008::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    return "错误码8 K_NOT_READY";
}

std::string KvcacheConnFault002_008::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    return "K_NOT_READY(8)表示Client未就绪，通常Init未完成或顺序错误，属于用户侧问题。（来源：08手册:L130）";
}

RootCause KvcacheConnFault002_008::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_008::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    return "检查业务侧Init调用和ConnectOptions配置顺序，确保在Put/Get前已完成Init。（来源：08手册:L248）";
}

std::string KvcacheConnFault002_008::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L269, L271, L130
    return "通过access log识别（来源：08手册:L130, L189）：access log中status_code（第8列）为8。（来源：08手册:L130）";
}

std::string KvcacheConnFault002_008::GetId() const
{
    return "kvcache_conn_fault_002_008";
}

} // namespace diag

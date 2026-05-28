#include "kvcache_conn_fault_002_007.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"
#include <iostream>

namespace diag {

// 故障编码: kvcache_conn_fault_002_007 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130)
static AutoRegister<KvcacheConnFault002_007> g_kvcacheconnfault002_007("kvcache_conn_fault_002_007");

bool KvcacheConnFault002_007::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG | sort | uniq -c | grep -w 3");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=3的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"3\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_007::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    return "错误码3 K_NOT_FOUND";
}

std::string KvcacheConnFault002_007::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    return "K_NOT_FOUND(3)表示对象不存在，属于用户侧问题。（来源：08手册:L130）";
}

RootCause KvcacheConnFault002_007::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_007::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    return "业务方自查key正确性和Put/Get顺序。（来源：08手册:L251）";
}

std::string KvcacheConnFault002_007::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L253, L255, L130
    return "通过access log识别（来源：08手册:L130, L189）：access log中status_code（第8列）为3。（来源：08手册:L130）";
}

std::string KvcacheConnFault002_007::GetId() const
{
    return "kvcache_conn_fault_002_007";
}

} // namespace diag

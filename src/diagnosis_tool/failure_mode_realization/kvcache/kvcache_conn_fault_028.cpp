#include "kvcache_conn_fault_028.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138)
static AutoRegister<KvcacheConnFault028> g_kvcacheconnfault028("kvcache_conn_fault_028");

bool KvcacheConnFault028::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -E '1004|1006|1008|1009|1010'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    return "URMA故障（1004-1010）";
}

std::string KvcacheConnFault028::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    return "向下级匹配。（来源：08手册:L281-308）";
}

RootCause KvcacheConnFault028::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    return "向下级匹配。（来源：08手册:L281-308）";
}

std::string KvcacheConnFault028::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L856, L858-864, L137-138
    return "通过access log识别（来源：08手册:L137-138, L199）：access log中status_code（第8列）为1004/1006/1008/1009/1010；或通过Worker INFO log [URMA_前缀识别。（来源：08手册:L281-308）";
}

std::string KvcacheConnFault028::GetId() const
{
    return "kvcache_conn_fault_028";
}

} // namespace diag

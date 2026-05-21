#include "kvcache_conn_fault_002.h"
#include "../../failure_mode_factory.h"
#include "../urma/urma_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189)
static AutoRegister<KvcacheConnFault002> g_kvcacheconnfault002("kvcache_conn_fault_002");

bool KvcacheConnFault002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E 'DS_KV_CLIENT_(PUT|GET)' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | awk -F'|' '{gsub(/^ +| +$/,\"\",$8); gsub(/^ +| +$/,\"\",$13); print $8, $13}' | sort | uniq -c | head");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    return "用户侧错误（code=0/respMsg异常 + code=2/3/8）";
}

std::string KvcacheConnFault002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    return "向下级匹配。";
}

RootCause KvcacheConnFault002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    return "向下级匹配。";
}

std::string KvcacheConnFault002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L93, L127-189
    return "通过access log识别（来源：08手册:L127-130, L187-190）：查询access log respMsg，code=0配合respMsg异常、或code=2(K_INVALID)/3(K_NOT_FOUND)/8(K_NOT_READY)。";
}

std::string KvcacheConnFault002::GetId() const
{
    return "kvcache_conn_fault_002";
}

} // namespace diag

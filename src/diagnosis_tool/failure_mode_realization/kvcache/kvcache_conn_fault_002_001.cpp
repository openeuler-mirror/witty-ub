#include "kvcache_conn_fault_002_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_002_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247)
static AutoRegister<KvcacheConnFault002_001> g_kvcacheconnfault002_001("kvcache_conn_fault_002_001");

bool KvcacheConnFault002_001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E 'DS_KV_CLIENT_(PUT|GET)' $WITTY_UB_CLIENT_ACCESS_LOG | grep -E 'The objectKey is empty|dataSize should be bigger than zero|length not match'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault002_001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    return "respMsg参数非法类故障";
}

std::string KvcacheConnFault002_001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    return "业务参数非法，属于用户侧问题。（来源：08手册:L247）";
}

RootCause KvcacheConnFault002_001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault002_001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    return "业务方校验调用参数。（来源：08手册:L247）";
}

std::string KvcacheConnFault002_001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L124, L126-129, L247
    return "通过日志关键字识别（来源：08手册:L246-249）：匹配The objectKey is empty / dataSize should be bigger than zero / length not match。（来源：08手册:L247）";
}

std::string KvcacheConnFault002_001::GetId() const
{
    return "kvcache_conn_fault_002_001";
}

} // namespace diag

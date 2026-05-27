#include "kvcache_conn_fault_001.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_001 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75)
static AutoRegister<KvcacheConnFault001> g_kvcacheconnfault001("kvcache_conn_fault_001");

bool KvcacheConnFault001::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG | sort | uniq -c");
    // 来源: rule f - 获取原始日志行用于trace解析，提取所有status_code非0的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code != \"0\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault001::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    return "KVCache中断异常";
}

std::string KvcacheConnFault001::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    return "向下级匹配。";
}

RootCause KvcacheConnFault001::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault001::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    return "向下级匹配。";
}

std::string KvcacheConnFault001::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L14-17, L64-75
    return "通过接口日志识别（来源：08手册:L14-17）：查询access log错误码分布，非0错误码大量增多；或通过两类故障分流判断（来源：08手册:L72-75）：接口大量失败、code非0明显增多、进程挂、连接断。";
}

std::string KvcacheConnFault001::GetId() const
{
    return "kvcache_conn_fault_001";
}

} // namespace diag

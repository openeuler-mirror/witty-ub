#include "kvcache_conn_fault_028_003.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_003 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299)
static AutoRegister<KvcacheConnFault028_003> g_kvcacheconnfault028_003("kvcache_conn_fault_028_003");

bool KvcacheConnFault028_003::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && grep -E '\\[URMA_RECREATE_JFS\\]' \"$WITTY_UB_FAULT_LOG\"/datasystem_worker.INFO.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_003::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    return "URMA_RECREATE_JFS + cqeStatus=9（JFS异常自动重建）";
}

std::string KvcacheConnFault028_003::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    return "JFS ACK超时触发的自动重建，通常自愈；若失败则需进一步排查UMDK/驱动。（来源：08手册:L299）";
}

RootCause KvcacheConnFault028_003::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_003::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    return "若无URMA_RECREATE_JFS_FAILED则视为自愈成功无需处理；若有FAILED则见kvcache_conn_fault_028_004。（来源：08手册:L299）";
}

std::string KvcacheConnFault028_003::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L925, L927-928, L299
    return "通过日志关键字识别（来源：08手册:L299）：匹配[URMA_RECREATE_JFS]且cqeStatus=9。（来源：08手册:L299）";
}

std::string KvcacheConnFault028_003::GetId() const
{
    return "kvcache_conn_fault_028_003";
}

} // namespace diag

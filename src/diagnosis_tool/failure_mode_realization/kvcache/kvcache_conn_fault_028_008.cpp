#include "kvcache_conn_fault_028_008.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_028_008 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304)
static AutoRegister<KvcacheConnFault028_008> g_kvcacheconnfault028_008("kvcache_conn_fault_028_008");

bool KvcacheConnFault028_008::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log | sort | uniq -c | grep -w 1009");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=1009的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_FAULT_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"1009\" {print $0}' \"$WITTY_UB_FAULT_LOG\"/ds_client_access_*.log 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault028_008::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    return "错误码1009 K_URMA_CONNECT_FAILED（URMA建连失败）";
}

std::string KvcacheConnFault028_008::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    return "URMA建连失败，可能UB端口down或设备节点缺失，属于URMA责任。（来源：08手册:L304）";
}

RootCause KvcacheConnFault028_008::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_008::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    return "ifconfig ub0查端口up/down；ls /dev/ub*看设备节点是否存在。（来源：08手册:L304）";
}

std::string KvcacheConnFault028_008::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L1034, L1036, L304
    return "通过access log识别（来源：08手册:L304）：access log中status_code（第8列）为1009（K_URMA_CONNECT_FAILED）。（来源：08手册:L304）";
}

std::string KvcacheConnFault028_008::GetId() const
{
    return "kvcache_conn_fault_028_008";
}

} // namespace diag

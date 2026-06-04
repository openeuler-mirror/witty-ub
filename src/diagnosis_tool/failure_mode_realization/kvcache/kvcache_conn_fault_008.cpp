#include "kvcache_conn_fault_008.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_008 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132)
static AutoRegister<KvcacheConnFault008> g_kvcacheconnfault008("kvcache_conn_fault_008");

bool KvcacheConnFault008::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG | sort | uniq -c | grep -E '[[:space:]]7$'");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=7的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"7\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG $WITTY_UB_WORKER_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault008::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    return "错误码7 K_IO_ERROR (OS)";
}

std::string KvcacheConnFault008::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    return "IO错误，可能原因包括块设备/文件系统故障或分布式网盘POSIX接口失败。（来源：08手册:L331）";
}

RootCause KvcacheConnFault008::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault008::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    return "dmesg查看IO错误日志；查块设备/文件系统健康状态；分布式网盘POSIX接口失败同样归此类别。（来源：08手册:L331）";
}

std::string KvcacheConnFault008::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L384, L386, L132
    return "通过access log识别（来源：08手册:L132, L196）：access log中status_code（第8列）为7。（来源：08手册:L132）";
}

std::string KvcacheConnFault008::GetId() const
{
    return "kvcache_conn_fault_008";
}

} // namespace diag

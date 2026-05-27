#include "kvcache_conn_fault_009.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_009 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132)
static AutoRegister<KvcacheConnFault009> g_kvcacheconnfault009("kvcache_conn_fault_009");

bool KvcacheConnFault009::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' '{gsub(/^ +| +$/,\"\",$8); print $8}' $WITTY_UB_CLIENT_ACCESS_LOG | sort | uniq -c | grep -w 13");
    // 来源: rule f - 获取原始日志行用于trace解析，提取status_code=13的access log行
    std::string rawOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && awk -F'|' 'NR>0 {code=$8; gsub(/^ +| +$/,\"\",code)} code == \"13\" {print $0}' $WITTY_UB_CLIENT_ACCESS_LOG 2>/dev/null");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    rawOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(rawOutput);
    kvcache_log_helper::ParseFailureLogLine(rawOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault009::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    return "错误码13 K_NO_SPACE (OS)";
}

std::string KvcacheConnFault009::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    return "磁盘空间不足，属于OS层问题。（来源：08手册:L132）";
}

RootCause KvcacheConnFault009::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault009::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    return "df -h确认磁盘使用情况；检查resource.log中SPILL_HARD_DISK/SHARED_DISK字段；清理磁盘或扩容。（来源：08手册:L332）";
}

std::string KvcacheConnFault009::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L405, L407, L132
    return "通过access log识别（来源：08手册:L132, L196）：access log中status_code（第8列）为13；或df -h检查磁盘满。（来源：08手册:L132, L332）";
}

std::string KvcacheConnFault009::GetId() const
{
    return "kvcache_conn_fault_009";
}

} // namespace diag

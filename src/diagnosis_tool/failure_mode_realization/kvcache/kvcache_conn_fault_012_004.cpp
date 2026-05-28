#include "kvcache_conn_fault_012_004.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_012_004 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635)
static AutoRegister<KvcacheConnFault012_004> g_kvcacheconnfault012_004("kvcache_conn_fault_012_004");

bool KvcacheConnFault012_004::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG$WITTY_UB_WORKER_ACCESS_LOG\" && grep -E 'Cannot receive heartbeat from worker|\\[HealthCheck\\] Worker is exiting now|meta_is_moving' $WITTY_UB_WORKER_INFO_LOG $WITTY_UB_CLIENT_INFO_LOG 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault012_004::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    return "心跳/生命周期/扩缩容";
}

std::string KvcacheConnFault012_004::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    return "分为三种情况（来源：08手册:L274）：心跳断kill -CONT恢复；退出由编排自动拉起；扩缩容SDK自重试。";
}

RootCause KvcacheConnFault012_004::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_004::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    return "心跳断→kill -CONT <pid>；退出由编排拉起；扩缩容SDK自重试。（来源：08手册:L274）";
}

std::string KvcacheConnFault012_004::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L590, L593-595, L274, L630-635
    return "通过日志关键字识别（来源：08手册:L274）：匹配Cannot receive heartbeat from worker / [HealthCheck] Worker is exiting now / meta_is_moving = true。（来源：08手册:L274, L630-635）";
}

std::string KvcacheConnFault012_004::GetId() const
{
    return "kvcache_conn_fault_012_004";
}

} // namespace diag

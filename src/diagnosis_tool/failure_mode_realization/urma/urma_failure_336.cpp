#include "urma_failure_336.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure336> g_urma("urma_336");

bool UrmaFailure336::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_register_health_ctx_global' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to alloc health ctx node'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure336::GetName() const
{
    return "健康检查相关临时结构或命令参数分配失败";
}

std::string UrmaFailure336::GetRootCauseDesc() const
{
    return "函数在分配健康检查前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure336::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure336::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure336::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_ctx_global，Failed to alloc health ctx node。";
}

std::string UrmaFailure336::GetId() const
{
    return "urma_336";
}

} // namespace diag

#include "urma_failure_065.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure065> g_urma("urma_065");

bool UrmaFailure065::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vjetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to fill health check seg info for vjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure065::GetName() const
{
    return "创建健康检查过程中依赖步骤失败";
}

std::string UrmaFailure065::GetRootCauseDesc() const
{
    return "函数用于创建健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure065::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure065::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure065::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjetty，Failed to fill health check seg info for vjetty。";
}

std::string UrmaFailure065::GetId() const
{
    return "urma_065";
}

} // namespace diag

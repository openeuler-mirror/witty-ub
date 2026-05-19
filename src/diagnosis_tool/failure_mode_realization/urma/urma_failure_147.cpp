#include "urma_failure_147.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure147> g_urma("urma_147");

bool UrmaFailure147::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_unbind_jetty_async' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Not allowed to call unbind as the tp mode of jetty :' | grep -F 'is:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure147::GetName() const
{
    return "urma_unbind_jetty_async 执行绑定 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure147::GetRootCauseDesc() const
{
    return "urma_unbind_jetty_async 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure147::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure147::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure147::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Not allowed to call unbind as the tp mode of jetty : is";
}

std::string UrmaFailure147::GetId() const
{
    return "urma_147";
}

} // namespace diag

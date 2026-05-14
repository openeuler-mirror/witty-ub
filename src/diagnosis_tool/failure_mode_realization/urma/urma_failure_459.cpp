#include "urma_failure_459.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure459> g_urma("urma_459");

bool UrmaFailure459::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_jetty_grp' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'delete_jetty_grp failed')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure459::GetName() const
{
    return "urma_create_jetty_grp 执行创建 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure459::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure459::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure459::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure459::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：delete_jetty_grp failed";
}

std::string UrmaFailure459::GetId() const
{
    return "urma_459";
}

} // namespace diag

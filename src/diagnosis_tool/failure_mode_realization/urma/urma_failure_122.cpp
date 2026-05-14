#include "urma_failure_122.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure122> g_urma("urma_122");

bool UrmaFailure122::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_active_jfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to exec ops->active_jfr')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure122::GetName() const
{
    return "urma_active_jfr 执行激活 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure122::GetRootCauseDesc() const
{
    return "urma_active_jfr 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure122::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure122::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure122::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to exec ops->active_jfr";
}

std::string UrmaFailure122::GetId() const
{
    return "urma_122";
}

} // namespace diag

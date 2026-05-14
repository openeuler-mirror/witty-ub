#include "urma_failure_412.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure412> g_urma("urma_412");

bool UrmaFailure412::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_set_jfr_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to exec urma_jfr_set_options')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure412::GetName() const
{
    return "urma_set_jfr_opt 执行设置 JFR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure412::GetRootCauseDesc() const
{
    return "urma_set_jfr_opt 调用下层 provider、bond 组件或系统接口处理 JFR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure412::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure412::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure412::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to exec urma_jfr_set_options";
}

std::string UrmaFailure412::GetId() const
{
    return "urma_412";
}

} // namespace diag

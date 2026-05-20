#include "urma_failure_488.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure488> g_urma("urma_488");

bool UrmaFailure488::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Cannot set aggregated mode for non-aggregated device'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure488::GetName() const
{
    return "urma_set_context_opt 执行设置 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure488::GetRootCauseDesc() const
{
    return "urma_set_context_opt 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure488::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure488::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure488::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Cannot set aggregated mode for non-aggregated device";
}

std::string UrmaFailure488::GetId() const
{
    return "urma_488";
}

} // namespace diag

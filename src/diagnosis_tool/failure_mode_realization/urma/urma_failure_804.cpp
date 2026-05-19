#include "urma_failure_804.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure804> g_urma("urma_804");

bool UrmaFailure804::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_notifier' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to delete notifier, ret:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure804::GetName() const
{
    return "urma_delete_notifier 执行删除 URMA 对象 失败导致当前资源状态无法推进";
}

std::string UrmaFailure804::GetRootCauseDesc() const
{
    return "urma_delete_notifier 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure804::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure804::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure804::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete notifier, ret";
}

std::string UrmaFailure804::GetId() const
{
    return "urma_804";
}

} // namespace diag

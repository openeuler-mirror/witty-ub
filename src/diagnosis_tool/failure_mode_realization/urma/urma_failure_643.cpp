#include "urma_failure_643.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure643> g_urma("urma_643");

bool UrmaFailure643::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'post_send_check_valid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'No bjetty_ctx')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure643::GetName() const
{
    return "post_send_check_valid 执行投递 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure643::GetRootCauseDesc() const
{
    return "post_send_check_valid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure643::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure643::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure643::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：No bjetty_ctx";
}

std::string UrmaFailure643::GetId() const
{
    return "urma_643";
}

} // namespace diag

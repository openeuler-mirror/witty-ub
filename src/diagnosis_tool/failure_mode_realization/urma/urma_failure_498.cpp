#include "urma_failure_498.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure498> g_urma("urma_498");

bool UrmaFailure498::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'get_dev_and_ctx_by_name' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get device'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure498::GetName() const
{
    return "get_dev_and_ctx_by_name 执行获取 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure498::GetRootCauseDesc() const
{
    return "get_dev_and_ctx_by_name 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure498::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure498::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure498::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get device";
}

std::string UrmaFailure498::GetId() const
{
    return "urma_498";
}

} // namespace diag

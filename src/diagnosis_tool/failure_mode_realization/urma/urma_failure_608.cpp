#include "urma_failure_608.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure608> g_urma("urma_608");

bool UrmaFailure608::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ref:' | "
        "grep -F ', not zero'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure608::GetName() const
{
    return "urma_free_token_id 执行释放 token_id 失败导致当前资源状态无法推进";
}

std::string UrmaFailure608::GetRootCauseDesc() const
{
    return "urma_free_token_id 调用下层 provider、bond 组件或系统接口处理 token_id 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure608::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure608::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure608::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ref:, not zero";
}

std::string UrmaFailure608::GetId() const
{
    return "urma_608";
}

} // namespace diag

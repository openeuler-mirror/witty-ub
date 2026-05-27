#include "urma_failure_404.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure404> g_urma("urma_404");

bool UrmaFailure404::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ref:' | "
        "grep -F 'u, not zero'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure404::GetName() const
{
    return "释放Token过程中依赖步骤失败";
}

std::string UrmaFailure404::GetRootCauseDesc() const
{
    return "函数用于释放Token，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure404::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure404::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure404::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_token_id，ref:，u, not zero";
}

std::string UrmaFailure404::GetId() const
{
    return "urma_404";
}

} // namespace diag

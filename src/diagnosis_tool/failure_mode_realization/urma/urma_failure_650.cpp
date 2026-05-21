#include "urma_failure_650.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure650> g_urma("urma_650");

bool UrmaFailure650::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'post_recv_check_valid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bjetty_ctx is NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure650::GetName() const
{
    return "post_recv_check_valid 执行投递 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure650::GetRootCauseDesc() const
{
    return "post_recv_check_valid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure650::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure650::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure650::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bjetty_ctx is NULL";
}

std::string UrmaFailure650::GetId() const
{
    return "urma_650";
}

} // namespace diag

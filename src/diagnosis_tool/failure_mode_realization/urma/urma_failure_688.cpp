#include "urma_failure_688.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure688> g_urma("urma_688");

bool UrmaFailure688::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'set_fd_noblock' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure688::GetName() const
{
    return "设置文件描述符过程中依赖步骤失败";
}

std::string UrmaFailure688::GetRootCauseDesc() const
{
    return "函数用于设置文件描述符，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次U"
           "RMA操作失败。";
}

RootCause UrmaFailure688::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure688::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure688::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：set_fd_noblock，ret:";
}

std::string UrmaFailure688::GetId() const
{
    return "urma_688";
}

} // namespace diag

#include "urma_failure_033.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure033> g_urma("urma_033");

bool UrmaFailure033::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init bitmap'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure033::GetName() const
{
    return "初始化URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure033::GetRootCauseDesc() const
{
    return "函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次U"
           "RMA操作失败。";
}

RootCause UrmaFailure033::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure033::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure033::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bdp_slide_wnd_init，Failed to init bitmap";
}

std::string UrmaFailure033::GetId() const
{
    return "urma_033";
}

} // namespace diag

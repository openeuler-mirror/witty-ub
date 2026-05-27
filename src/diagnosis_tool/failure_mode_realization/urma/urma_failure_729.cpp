#include "urma_failure_729.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure729> g_urma("urma_729");

bool UrmaFailure729::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_add' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param wnd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure729::GetName() const
{
    return "执行URMA资源所需输入对象无效导致设置URMA资源失败";
}

std::string UrmaFailure729::GetRootCauseDesc() const
{
    return "函数用于设置URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure729::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure729::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure729::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bdp_slide_wnd_add，Invalid param wnd";
}

std::string UrmaFailure729::GetId() const
{
    return "urma_729";
}

} // namespace diag

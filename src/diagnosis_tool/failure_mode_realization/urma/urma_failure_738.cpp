#include "urma_failure_738.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure738> g_urma("urma_738");

bool UrmaFailure738::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_add' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid param wnd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure738::GetName() const
{
    return "执行URMA资源所需输入对象无效导致设置URMA资源失败";
}

std::string UrmaFailure738::GetRootCauseDesc() const
{
    return "函数用于设置URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure738::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure738::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure738::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_add，Invalid param wnd。";
}

std::string UrmaFailure738::GetId() const
{
    return "urma_738";
}

} // namespace diag

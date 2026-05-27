#include "urma_failure_708.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure708> g_urma("urma_708");

bool UrmaFailure708::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ioctl "
        "failed in urma_cmd_deactive_jfr, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure708::GetName() const
{
    return "去激活ioctl的ioctl调用返回失败";
}

std::string UrmaFailure708::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交去激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结"
           "果。";
}

RootCause UrmaFailure708::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure708::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure708::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfr，ioctl failed in urma_cmd_deactive_jfr, ret:，, "
           "errno:。";
}

std::string UrmaFailure708::GetId() const
{
    return "urma_708";
}

} // namespace diag

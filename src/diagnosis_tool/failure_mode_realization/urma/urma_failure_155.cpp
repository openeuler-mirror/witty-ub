#include "urma_failure_155.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure155> g_urma("urma_155");

bool UrmaFailure155::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_set_jetty_opt, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure155::GetName() const
{
    return "设置ioctl的ioctl调用返回失败";
}

std::string UrmaFailure155::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交设置ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure155::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure155::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure155::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jetty_opt，ioctl failed in urma_cmd_set_jetty_opt, ret:，, errno:";
}

std::string UrmaFailure155::GetId() const
{
    return "urma_155";
}

} // namespace diag

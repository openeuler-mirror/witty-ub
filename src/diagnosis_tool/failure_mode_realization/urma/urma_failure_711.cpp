#include "urma_failure_711.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure711> g_urma("urma_711");

bool UrmaFailure711::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ioctl_wait_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'wait jfc ioctl failed, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure711::GetName() const
{
    return "执行wait jfc驱动命令的ioctl调用返回失败";
}

std::string UrmaFailure711::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交执行wait "
           "jfc驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。";
}

RootCause UrmaFailure711::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure711::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure711::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_wait_jfc，wait jfc ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure711::GetId() const
{
    return "urma_711";
}

} // namespace diag

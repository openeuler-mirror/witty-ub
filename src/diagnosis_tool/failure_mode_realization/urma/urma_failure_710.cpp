#include "urma_failure_710.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure710> g_urma("urma_710");

bool UrmaFailure710::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_tlv_ioctl' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'ioctl "
        "failed, ret:' | grep -F ', errno:' | grep -F ', cmd:' | grep -F ', kdrv_err:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure710::GetName() const
{
    return "执行ioctl的ioctl调用返回失败";
}

std::string UrmaFailure710::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交执行ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生"
           "在内核态驱动";
}

RootCause UrmaFailure710::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure710::GetFixSuggDesc() const
{
    return "UDMA驱动相关，需进一步排查硬件";
}

std::string UrmaFailure710::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_tlv_ioctl，ioctl failed, ret:，, errno:，, cmd:，, kdrv_err:。";
}

std::string UrmaFailure710::GetId() const
{
    return "urma_710";
}

} // namespace diag

#include "urma_failure_702.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure702> g_urma("urma_702");

bool UrmaFailure702::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_tlv_ioctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed, ret:' | grep -F ', errno:' | grep -F ', cmd:' | grep -F ', kdrv_err:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure702::GetName() const
{
    return "执行ioctl的ioctl调用返回失败";
}

std::string UrmaFailure702::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交执行ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生"
           "在内核态驱动";
}

RootCause UrmaFailure702::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure702::GetFixSuggDesc() const
{
    return "UDMA驱动相关，需进一步排查硬件";
}

std::string UrmaFailure702::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_tlv_ioctl，ioctl failed, ret:，, errno:，, cmd:，, kdrv_err:";
}

std::string UrmaFailure702::GetId() const
{
    return "urma_702";
}

} // namespace diag

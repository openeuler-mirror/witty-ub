#include "urma_failure_095.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure095> g_urma("urma_095");

bool UrmaFailure095::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_tlv_ioctl' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed, ret:' | "
        "grep -F ', errno:' | "
        "grep -F ', cmd:' | "
        "grep -F ', kdrv_err:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure095::GetName() const
{
    return "urma_tlv_ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure095::GetRootCauseDesc() const
{
    return "urma_tlv_ioctl URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失"
           "败，并且errno为特定的2048，故障发生在内核态驱动";
}

RootCause UrmaFailure095::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure095::GetFixSuggDesc() const
{
    return "UDMA驱动相关，需进一步排查硬件";
}

std::string UrmaFailure095::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中依次匹配关键日志：ioctl failed, ret:、, errno:、, cmd:、, kdrv_err:";
}

std::string UrmaFailure095::GetId() const
{
    return "urma_095";
}

} // namespace diag

#include "urma_failure_095.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure095> g_urma("urma_095");

bool UrmaFailure095::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'ATTR_ARRAY' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'ioctl failed, ret:, errno:, cmd:, kdrv_err')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure095::GetName() const
{
    return "ATTR_ARRAY out type init ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure095::GetRootCauseDesc() const
{
    return "ATTR_ARRAY 通过 fd 向内核驱动下发out type init请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 URMA 对象 状态。";
}

RootCause UrmaFailure095::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure095::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure095::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ioctl failed, ret:, errno:, cmd:, kdrv_err";
}

std::string UrmaFailure095::GetId() const
{
    return "urma_095";
}

} // namespace diag

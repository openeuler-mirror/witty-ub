#include "urma_failure_714.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure714> g_urma("urma_714");

bool UrmaFailure714::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_discover_devices' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed close dir:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure714::GetName() const
{
    return "分配设备过程中依赖步骤失败";
}

std::string UrmaFailure714::GetRootCauseDesc() const
{
    return "函数用于分配设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure714::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure714::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure714::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_discover_devices，Failed close dir:，, errno:。";
}

std::string UrmaFailure714::GetId() const
{
    return "urma_714";
}

} // namespace diag

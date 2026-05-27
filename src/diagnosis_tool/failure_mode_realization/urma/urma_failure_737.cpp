#include "urma_failure_737.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure737> g_urma("urma_737");

bool UrmaFailure737::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_slide_wnd_has' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Seq larger than total size of bitmap'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure737::GetName() const
{
    return "设置URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure737::GetRootCauseDesc() const
{
    return "函数用于设置URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure737::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure737::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure737::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_has，Seq larger than total size of bitmap。";
}

std::string UrmaFailure737::GetId() const
{
    return "urma_737";
}

} // namespace diag

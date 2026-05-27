#include "urma_failure_519.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure519> g_urma("urma_519");

bool UrmaFailure519::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to create vseg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure519::GetName() const
{
    return "Segment创建时下层资源准备失败";
}

std::string UrmaFailure519::GetRootCauseDesc() const
{
    return "函数负责创建Segment，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure519::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure519::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure519::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vseg，Failed to create vseg。";
}

std::string UrmaFailure519::GetId() const
{
    return "urma_519";
}

} // namespace diag

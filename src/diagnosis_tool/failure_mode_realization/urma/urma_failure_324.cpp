#include "urma_failure_324.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure324> g_urma("urma_324");

bool UrmaFailure324::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pjfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure324::GetName() const
{
    return "物理 JFC创建时下层资源准备失败";
}

std::string UrmaFailure324::GetRootCauseDesc() const
{
    return "函数负责创建物理 JFC，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure324::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure324::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure324::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_pjfc，Failed to create pjfc";
}

std::string UrmaFailure324::GetId() const
{
    return "urma_324";
}

} // namespace diag

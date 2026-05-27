#include "urma_failure_084.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure084> g_urma("urma_084");

bool UrmaFailure084::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to import pjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure084::GetName() const
{
    return "物理 Jetty导入时下层资源准备失败";
}

std::string UrmaFailure084::GetRootCauseDesc() const
{
    return "函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure084::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure084::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure084::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pjetty，Failed to import pjetty";
}

std::string UrmaFailure084::GetId() const
{
    return "urma_084";
}

} // namespace diag

#include "urma_failure_064.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure064> g_urma("urma_064");

bool UrmaFailure064::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure064::GetName() const
{
    return "物理 Jetty创建时下层资源准备失败";
}

std::string UrmaFailure064::GetRootCauseDesc() const
{
    return "函数负责创建物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure064::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure064::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure064::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_pjetty，Failed to create pjetty";
}

std::string UrmaFailure064::GetId() const
{
    return "urma_064";
}

} // namespace diag

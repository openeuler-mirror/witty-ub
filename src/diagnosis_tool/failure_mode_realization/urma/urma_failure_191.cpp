#include "urma_failure_191.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure191> g_urma("urma_191");

bool UrmaFailure191::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure191::GetName() const
{
    return "bondp_create_pjetty 执行创建 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure191::GetRootCauseDesc() const
{
    return "bondp_create_pjetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure191::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure191::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure191::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create pjetty";
}

std::string UrmaFailure191::GetId() const
{
    return "urma_191";
}

} // namespace diag

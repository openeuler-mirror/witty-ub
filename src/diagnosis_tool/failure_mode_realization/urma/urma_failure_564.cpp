#include "urma_failure_564.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure564> g_urma("urma_564");

bool UrmaFailure564::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'import_pjetty_for_port_eid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to import direct tjetty')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure564::GetName() const
{
    return "import_pjetty_for_port_eid 执行导入 EID 失败导致当前资源状态无法推进";
}

std::string UrmaFailure564::GetRootCauseDesc() const
{
    return "import_pjetty_for_port_eid 调用下层 provider、bond 组件或系统接口处理 EID 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure564::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure564::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure564::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to import direct tjetty";
}

std::string UrmaFailure564::GetId() const
{
    return "urma_564";
}

} // namespace diag

#include "urma_failure_576.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure576> g_urma("urma_576");

bool UrmaFailure576::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'import_pseg_for_port_eid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'No valid direct route')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure576::GetName() const
{
    return "import_pseg_for_port_eid 校验 EID 业务条件不满足导致导入流程拒绝继续执行";
}

std::string UrmaFailure576::GetRootCauseDesc() const
{
    return "import_pseg_for_port_eid 在执行导入时发现 EID "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure576::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure576::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure576::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：No valid direct route";
}

std::string UrmaFailure576::GetId() const
{
    return "urma_576";
}

} // namespace diag

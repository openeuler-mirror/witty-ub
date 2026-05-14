#include "urma_failure_466.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure466> g_urma("urma_466");

bool UrmaFailure466::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_alloc_token_id_ex' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'dev not support token id table mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure466::GetName() const
{
    return "urma_alloc_token_id_ex 校验 设备 业务条件不满足导致分配流程拒绝继续执行";
}

std::string UrmaFailure466::GetRootCauseDesc() const
{
    return "urma_alloc_token_id_ex 在执行分配时发现 设备 "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure466::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure466::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure466::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：dev not support token id table mode";
}

std::string UrmaFailure466::GetId() const
{
    return "urma_466";
}

} // namespace diag

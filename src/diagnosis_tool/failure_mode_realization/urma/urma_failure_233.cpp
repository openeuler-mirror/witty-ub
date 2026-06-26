#include "urma_failure_233.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure233> g_urma("urma_233");

bool UrmaFailure233::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pcontext") != std::string::npos &&
           message.find("Failed to create context for primary eid, dev:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure233::GetName() const
{
    return "下层资源创建失败导致创建pcontext失败";
}

std::string UrmaFailure233::GetRootCauseDesc() const
{
    return "bondp_create_pcontext在创建pcontext过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure233::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure233::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure233::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pcontext，Failed to create context for primary eid, "
           "dev:，, eid_id"
           "x:。";
}

std::string UrmaFailure233::GetId() const
{
    return "urma_233";
}
} // namespace diag

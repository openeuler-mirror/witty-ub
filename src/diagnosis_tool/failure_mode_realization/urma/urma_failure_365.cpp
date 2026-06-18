#include "urma_failure_365.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure365> g_urma("urma_365");

bool UrmaFailure365::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfc") != std::string::npos &&
           message.find("Failed to create vjfc, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure365::GetName() const
{
    return "下层资源创建失败导致创建JFC失败";
}

std::string UrmaFailure365::GetRootCauseDesc() const
{
    return "bondp_create_jfc在创建JFC过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure365::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure365::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure365::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfc，Failed to create vjfc, dev_name:，, eid_idx:。";
}

std::string UrmaFailure365::GetId() const
{
    return "urma_365";
}
} // namespace diag

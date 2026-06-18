#include "urma_failure_136.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure136> g_urma("urma_136");

bool UrmaFailure136::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jfs") != std::string::npos &&
           message.find("Failed to create vjfs") != std::string::npos;
}

std::string UrmaFailure136::GetName() const
{
    return "下层资源创建失败导致创建JFS失败";
}

std::string UrmaFailure136::GetRootCauseDesc() const
{
    return "bondp_create_jfs在创建JFS过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure136::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure136::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure136::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jfs，Failed to create vjfs。";
}

std::string UrmaFailure136::GetId() const
{
    return "urma_136";
}
} // namespace diag

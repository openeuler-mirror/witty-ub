#include "urma_failure_158.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure158> g_urma("urma_158");

bool UrmaFailure158::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vcontext") != std::string::npos &&
           message.find("Failed to create context, ret:") != std::string::npos;
}

std::string UrmaFailure158::GetName() const
{
    return "下层资源创建失败导致创建vcontext失败";
}

std::string UrmaFailure158::GetRootCauseDesc() const
{
    return "bondp_create_vcontext在创建vcontext过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure158::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure158::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure158::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vcontext，Failed to create context, ret:。";
}

std::string UrmaFailure158::GetId() const
{
    return "urma_158";
}
} // namespace diag

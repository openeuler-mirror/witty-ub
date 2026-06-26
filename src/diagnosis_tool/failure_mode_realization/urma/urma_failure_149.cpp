#include "urma_failure_149.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure149> g_urma("urma_149");

bool UrmaFailure149::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_jetty") != std::string::npos &&
           message.find("Failed to create pjetty") != std::string::npos;
}

std::string UrmaFailure149::GetName() const
{
    return "下层资源创建失败导致创建Jetty失败";
}

std::string UrmaFailure149::GetRootCauseDesc() const
{
    return "bondp_create_jetty在创建Jetty过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure149::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure149::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure149::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_jetty，Failed to create pjetty。";
}

std::string UrmaFailure149::GetId() const
{
    return "urma_149";
}
} // namespace diag

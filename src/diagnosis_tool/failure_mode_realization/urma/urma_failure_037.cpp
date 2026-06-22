#include "urma_failure_037.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure037> g_urma("urma_037");

bool UrmaFailure037::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jetty") != std::string::npos &&
           message.find("failed to init create jetty cmd") != std::string::npos;
}

std::string UrmaFailure037::GetName() const
{
    return "下层资源创建失败导致创建Jetty失败";
}

std::string UrmaFailure037::GetRootCauseDesc() const
{
    return "urma_cmd_create_jetty在创建Jetty过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure037::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure037::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure037::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty，failed to init create jetty cmd。";
}

std::string UrmaFailure037::GetId() const
{
    return "urma_037";
}
} // namespace diag

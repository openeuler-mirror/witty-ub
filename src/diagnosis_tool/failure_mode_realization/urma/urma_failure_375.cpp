#include "urma_failure_375.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure375> g_urma("urma_375");

bool UrmaFailure375::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("comp_post_recv") != std::string::npos &&
           message.find("Invalid post jfr wr type:") != std::string::npos;
}

std::string UrmaFailure375::GetName() const
{
    return "COMP状态不满足要求导致投递COMP失败";
}

std::string UrmaFailure375::GetRootCauseDesc() const
{
    return "comp_post_recv执行投递COMP时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure375::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure375::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure375::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：comp_post_recv，Invalid post jfr wr type:。";
}

std::string UrmaFailure375::GetId() const
{
    return "urma_375";
}
} // namespace diag

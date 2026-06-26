#include "urma_failure_316.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure316> g_urma("urma_316");

bool UrmaFailure316::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_seg") != std::string::npos &&
           message.find("Failed to create pseg") != std::string::npos;
}

std::string UrmaFailure316::GetName() const
{
    return "下层资源创建失败导致注册Segment失败";
}

std::string UrmaFailure316::GetRootCauseDesc() const
{
    return "bondp_register_seg在注册Segment过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure316::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure316::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure316::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_seg，Failed to create pseg。";
}

std::string UrmaFailure316::GetId() const
{
    return "urma_316";
}
} // namespace diag

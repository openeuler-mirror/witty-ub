#include "urma_0998_resource_import_register_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0998ResourceImportRegisterFailure> g_urma("urma_0998");

bool Urma0998ResourceImportRegisterFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0999", "urma_1001", "urma_1003", "urma_1008", "urma_1013",
                                                    "urma_1015", "urma_1017", "urma_1020", "urma_1023", "urma_1025",
                                                    "urma_1028", "urma_1031", "urma_1034", "urma_1036", "urma_1040"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0998ResourceImportRegisterFailure::GetName() const
{
    return "资源导入/注册失败";
}

std::string Urma0998ResourceImportRegisterFailure::GetRootCauseDesc() const
{
    return "向下级匹配。";
}

RootCause Urma0998ResourceImportRegisterFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0998ResourceImportRegisterFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0998ResourceImportRegisterFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0998ResourceImportRegisterFailure::GetId() const
{
    return "urma_0998";
}
} // namespace diag
